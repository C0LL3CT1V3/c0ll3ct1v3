module Markets
  class DiscoveryPercentile
    def self.live(prediction)
      scope = prediction.market.predictions
      ratio(later: scope.where("created_at > ?", prediction.created_at).count, total: scope.count)
    end

    def self.among_correct(prediction)
      scope = prediction.market.predictions.where(side: prediction.market.outcome)
      ratio(later: scope.where("created_at > ?", prediction.created_at).count, total: scope.count)
    end

    def self.ratio(later:, total:)
      return 0.0 if total.zero?

      later.to_f / total
    end
    private_class_method :ratio
  end
end
