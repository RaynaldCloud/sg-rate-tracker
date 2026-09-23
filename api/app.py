"""Flask REST API for serving scraped interest rates."""
from flask import Flask, jsonify, request

from database.db import get_latest_rates, get_rate_history, init_db


def create_app() -> Flask:
    """Build and configure the Flask app."""
    app = Flask(__name__)
    init_db()

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/rates")
    def latest_rates():
        """Latest rate for every bank and product, highest first.
        Optional filter: ?product=Fixed Deposit"""
        rates = get_latest_rates()
        product = request.args.get("product")
        if product:
            rates = [r for r in rates if r["product"].lower() == product.lower()]
        return jsonify(count=len(rates), rates=rates)

    @app.get("/api/rates/history")
    def rate_history():
        """Full history for one product.
        Required: ?bank=...&product=...  Optional: &tenure_months=12"""
        bank = request.args.get("bank")
        product = request.args.get("product")
        if not bank or not product:
            return jsonify(error="'bank' and 'product' query parameters are required"), 400
        tenure = request.args.get("tenure_months", type=int)
        min_deposit = request.args.get("min_deposit", type=float)
        history = get_rate_history(bank, product, tenure, min_deposit)
        return jsonify(bank=bank, product=product, tenure_months=tenure,
                       min_deposit=min_deposit, count=len(history), history=history)

    @app.errorhandler(404)
    def not_found(error):
        return jsonify(error="Not found"), 404

    return app


app = create_app()