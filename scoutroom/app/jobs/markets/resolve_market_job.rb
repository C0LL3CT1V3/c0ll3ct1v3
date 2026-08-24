module Markets
  class ResolveMarketJob < ApplicationJob
    queue_as :default

    def perform(market_id)
      market = Market.find(market_id)
      return unless market.resolved_at.present?

      if market.void?
        refund!(market)
      else
        pay_winners!(market)
      end

      refresh_slips!(market)
    end

    private

    def refund!(market)
      market.predictions.find_each do |prediction|
        next if PointsLedgerEntry.exists?(reference: prediction, kind: :refund)

        PointsLedger.record!(
          user: prediction.user,
          amount: prediction.points_staked,
          kind: :refund,
          reference: prediction
        )
      end
    end

    def pay_winners!(market)
      entries = market.predictions.order(:id).map do |prediction|
        {
          prediction: prediction,
          side: prediction.side,
          points_staked: prediction.points_staked,
          implied_probability_at_entry: prediction.implied_probability_at_entry
        }
      end

      payouts = Markets::PriceEngine.payouts(entries: entries, outcome: market.outcome)

      entries.each_with_index do |entry, index|
        payout = payouts[index]
        next unless payout

        prediction = entry[:prediction]
        prediction.update!(payout_multiplier: payout.multiplier)
        next if PointsLedgerEntry.exists?(reference: prediction, kind: :payout)

        PointsLedger.record!(
          user: prediction.user,
          amount: payout.credit,
          kind: :payout,
          reference: prediction
        )
      end
    end

    def refresh_slips!(market)
      return if market.void?

      market.predictions.includes(:slip).find_each do |prediction|
        slip = prediction.slip
        next unless slip
        next unless prediction.winner?

        slip.update!(discovery_percentile: Markets::DiscoveryPercentile.among_correct(prediction))
      end
    end
  end
end
