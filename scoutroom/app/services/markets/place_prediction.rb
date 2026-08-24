module Markets
  class PlacePrediction
    class Error < StandardError; end

    def self.call(user:, market:, side:, points:, thesis_tags: [], thesis_text: nil)
      new(user:, market:, side:, points:, thesis_tags:, thesis_text:).call
    end

    def initialize(user:, market:, side:, points:, thesis_tags:, thesis_text:)
      @user = user
      @market = market
      @side = side.to_s
      @points = points.to_i
      @thesis_tags = Array(thesis_tags).compact_blank
      @thesis_text = thesis_text.to_s.strip.presence
    end

    def call
      Prediction.transaction do
        @user.lock!
        @market.lock!

        raise Error, "This call is closed." unless @market.open_for_entry?
        raise Error, "You already called this one." if @user.predictions.exists?(market_id: @market.id)
        raise Error, "Stake at least 1 point." unless @points.positive?
        raise Error, "Pick yes or no." unless Prediction::SIDES.include?(@side)

        quote = Markets::PriceEngine.quote(real_yes: @market.real_yes_points, real_no: @market.real_no_points)
        p_entry = quote.for_side(@side)

        prediction = @market.predictions.create!(
          user: @user,
          side: @side,
          points_staked: @points,
          implied_probability_at_entry: p_entry,
          thesis_tags: @thesis_tags,
          thesis_text: @thesis_text
        )

        PointsLedger.record!(user: @user, amount: -@points, kind: :stake, reference: prediction)
        Slips::GenerateJob.perform_later(prediction.id)
        prediction
      end
    rescue PointsLedger::InsufficientPoints
      raise Error, "Not enough points."
    end
  end
end
