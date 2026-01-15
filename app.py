import os
import uuid
import requests
from flask import Flask, render_template, request
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Connexion Supabase et NOWPayments
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
NP_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")


@app.route('/')
def home():
    response = supabase.table("produits").select("*").execute()
    return render_template('index.html', produits=response.data)


@app.route('/payer/<int:produit_id>', methods=['POST'])
def payer(produit_id):
    # 1. Récupérer le produit (colonne prix_usd)
    res = supabase.table("produits").select("*").eq("id", produit_id).single().execute()
    produit = res.data

    # 2. On force le Litecoin (LTC)
    crypto = "ltc"

    # 3. Appel API NOWPayments
    headers = {"x-api-key": NP_API_KEY, "Content-Type": "application/json"}
    payload = {
        "price_amount": produit['prix_usd'],
        "price_currency": "usd",
        "pay_currency": "ltc",
        "order_id": str(uuid.uuid4()),
        "order_description": produit['nom']
    }

    try:
        response = requests.post("https://api.nowpayments.io/v1/payment", json=payload, headers=headers)
        data = response.json()
        return render_template('paiement_info.html',
                               adresse=data['pay_address'],
                               montant=data['pay_amount'],
                               crypto="LTC",
                               order_id=payload['order_id'])
    except Exception as e:
        return f"Erreur : {e}"


if __name__ == '__main__':

    @app.route('/webhook', methods=['POST'])
    def webhook():
        # NOWPayments nous envoie les détails du paiement ici
        data = request.json
        status = data.get('payment_status')
        order_id = data.get('order_id')

        # Si le paiement est terminé avec succès
        if status == 'finished':
            print(f"✅ Paiement reçu pour la commande {order_id}")
            # On met à jour le statut dans ta table Supabase
            supabase.table("commandes").update({"statut": "payé"}).eq("order_id", order_id).execute()

        return "OK", 200

    app.run(debug=True)