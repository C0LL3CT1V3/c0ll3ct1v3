module Tips
  class ProcessWebhook
    def self.call(event)
      new(event).call
    end

    def initialize(event)
      @event = event
    end

    def call
      case @event["type"]
      when "checkout.session.completed"
        complete_session(@event["data"]["object"])
      when "payment_intent.payment_failed"
        fail_intent(@event["data"]["object"])
      end
    end

    private

    def complete_session(session)
      tip = Tip.find_by(id: session.dig("metadata", "tip_id"))
      return unless tip

      tip.update!(
        status: :succeeded,
        stripe_payment_intent_id: session["payment_intent"]
      )
    end

    def fail_intent(intent)
      tip = Tip.find_by(stripe_payment_intent_id: intent["id"]) ||
            Tip.find_by(id: intent.dig("metadata", "tip_id"))
      return unless tip

      tip.update!(status: :failed)
    end
  end
end
