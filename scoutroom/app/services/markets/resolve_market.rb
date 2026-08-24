module Markets
  class ResolveMarket
    class Error < StandardError; end

    def self.call(market:, outcome:, note: nil)
      new(market:, outcome:, note:).call
    end

    def initialize(market:, outcome:, note:)
      @market = market
      @outcome = outcome.to_s
      @note = note
    end

    def call
      raise Error, "Choose yes, no, or void." unless %w[yes no void].include?(@outcome)

      Market.transaction do
        @market.lock!
        raise Error, "Already resolved." if @market.resolved_at.present?

        @market.update!(
          outcome: @outcome,
          resolved_at: Time.current,
          resolution_note: @note
        )
      end

      Markets::ResolveMarketJob.perform_later(@market.id)
      @market
    end
  end
end
