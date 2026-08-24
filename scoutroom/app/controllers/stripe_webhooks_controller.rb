class StripeWebhooksController < ApplicationController
  skip_before_action :verify_authenticity_token

  def create
    payload = request.body.read
    secret = ENV["STRIPE_WEBHOOK_SECRET"]
    event = if secret.present?
      Stripe::Webhook.construct_event(payload, request.env["HTTP_STRIPE_SIGNATURE"], secret)
    else
      JSON.parse(payload)
    end
    Tips::ProcessWebhook.call(event)
    head :ok
  rescue JSON::ParserError, Stripe::SignatureVerificationError
    head :bad_request
  end
end
