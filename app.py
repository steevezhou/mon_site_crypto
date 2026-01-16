import os
import uuid
import requests
from flask import Flask, render_template, request
from supabase import create_client
from dotenv import load_dotenv

# 1. Chargement des configurations
load_dotenv()

# 2. Création de l'application Flask
app = Flask(__name__)

# 3. Connexion aux services (Supabase et NOWPayments)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
NP_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")


# --- ROUTES ---

@app.route('/')
def home():
    """Affiche la boutique avec les produits depuis Supabase."""
    response = supabase.table("produits").select("*").execute()
    return render_template('index.html', produits=response.data)


@app.route('/payer/<int:produit_id>', methods=['POST'])
def payer(produit_id):
    """Crée une session de paiement NOWPayments en LTC."""
    # Récupérer le produit (on utilise la colonne prix_usd)
    res = supabase.table("produits").select("*").eq("id", produit_id).single().execute()
    produit = res.data

    # Appel à l'API NOWPayments
    url_api = "https://api.nowpayments.io/v1/payment"
    headers = {
        "x-api-key": NP_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "price_amount": produit['prix_usd'],  # Montant en USD depuis ta base
        "price_currency": "usd",
        "pay_currency": "ltc",  # Forcé en Litecoin
        "order_id": str(uuid.uuid4()),
        "order_description": produit['nom']
    }

    try:
        response = requests.post(url_api, json=payload, headers=headers)
        data = response.json()

        # Redirection vers la page d'infos de paiement
        return render_template('paiement_info.html',
                               adresse=data['pay_address'],
                               montant=data['pay_amount'],
                               crypto="LTC",
                               order_id=payload['order_id'])
    except Exception as e:
        return f"Erreur lors de la création du paiement : {e}"


@app.route('/webhook', methods=['POST'])
def webhook():
    """Route invisible que NOWPayments appelle pour confirmer le paiement."""
    data = request.json
    status = data.get('payment_status')
    order_id = data.get('order_id')

    # L'alignement ici est TRÈS important (4 espaces ou 1 tab)
    if status == 'finished':
        print(f"✅ Paiement confirmé pour la commande : {order_id}")
        # On pourrait ici marquer la commande comme payée dans Supabase

    return "OK", 200


@app.route('/success')
def success():
    """Page affichée au client après son paiement."""
    return render_template('success.html')


# --- LANCEMENT ---
if __name__ == '__main__':
    app.run(debug=True)
