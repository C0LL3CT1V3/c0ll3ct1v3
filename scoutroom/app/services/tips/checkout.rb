module Tips
  class Checkout
    class Error < StandardError; end

    def self.call(user:, artist:, amount_cents:, success_url:, cancel_url:)
      raise Error, "This artist has not connected payouts." unless artist.stripe_account_id.present?
      raise Error, "Stripe is not configured." if ENV["STRIPE_SECRET_KEY"].blank?
      raise Error, "Tip at least $1." if amount_cents.to_i < 100

      tip = Tip.create!(user:, artist:, amount_cents: amount_cents.to_i, status: :pending)

      session = Stripe::Checkout::Session.create(
        mode: "payment",
        line_items: [ {
          price_data: {
            currency: "usd",
            product_data: { name: "Boost #{artist.name}" },
            unit_amount: tip.amount_cents
          },
          quantity: 1
        } ],
        payment_intent_data: {
          transfer_data: { destination: artist.stripe_account_id },
          metadata: { tip_id: tip.id }
        },
        metadata: { tip_id: tip.id },
        success_url: success_url,
        cancel_url: cancel_url
      )

      [ tip, session.url ]
    end
  end
end
