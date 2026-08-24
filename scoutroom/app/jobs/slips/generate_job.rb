module Slips
  class GenerateJob < ApplicationJob
    queue_as :default

    def perform(prediction_id)
      prediction = Prediction.find(prediction_id)
      return if prediction.slip&.image&.attached?

      slip = prediction.slip || prediction.create_slip!(
        seed: seed_for(prediction),
        discovery_percentile: Markets::DiscoveryPercentile.live(prediction),
        thesis_tags: prediction.thesis_tags,
        thesis_text: prediction.thesis_text
      )

      svg = Slips::SvgRenderer.new(slip).render
      slip.image.attach(
        io: StringIO.new(svg),
        filename: "slip-#{slip.seed[0, 12]}.svg",
        content_type: "image/svg+xml"
      )
    end

    private

    def seed_for(prediction)
      Digest::SHA256.hexdigest(
        [
          prediction.user_id,
          prediction.market_id,
          prediction.created_at.to_i,
          prediction.points_staked
        ].join(":")
      )
    end
  end
end
