module Profiles
  class Stats
    Badge = Data.define(:key, :label)

    def initialize(user)
      @user = user
    end

    def badges
      list = []
      list << Badge.new(key: "first_wave", label: "First wave") if first_wave?
      list << Badge.new(key: "early_hit", label: "Early hit") if early_hit?
      list << Badge.new(key: "streak", label: "Hot streak") if streak?
      list
    end

    def leaderboard_score
      resolved = @user.predictions.joins(:market).merge(Market.resolved)
      return 0 if resolved.none?

      resolved.sum do |prediction|
        next 0 unless prediction.winner?

        (100 * (1.0 / prediction.implied_probability_at_entry.to_f)).round
      end
    end

    private

    def first_wave?
      @user.predictions.any? do |prediction|
        earlier = prediction.market.predictions.where("created_at < ?", prediction.created_at).count
        earlier < 10
      end
    end

    def early_hit?
      @user.predictions.includes(:slip, :market).any? do |prediction|
        prediction.winner? && prediction.slip && prediction.slip.discovery_percentile.to_f >= 0.5
      end
    end

    def streak?
      results = @user.predictions.joins(:market).merge(Market.resolved).order(:created_at).map(&:winner?)
      results.each_cons(3).any? { |window| window.all? }
    end
  end
end
