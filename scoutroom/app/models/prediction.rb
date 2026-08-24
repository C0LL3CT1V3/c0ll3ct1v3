class Prediction < ApplicationRecord
  THESIS_TAGS = %w[
    sound_songwriting
    live_show_energy
    playlist_momentum
    cosign_feature
    visual_identity
    fanbase_growth
    timing_scene_moment
  ].freeze

  SIDES = %w[yes no].freeze

  belongs_to :user
  belongs_to :market
  has_one :slip, dependent: :destroy

  enum :side, SIDES.index_by(&:itself), validate: true

  validates :points_staked, numericality: { only_integer: true, greater_than: 0 }
  validates :implied_probability_at_entry, numericality: { greater_than: 0, less_than: 1 }
  validates :user_id, uniqueness: { scope: :market_id, message: "already called this market" }
  validate :thesis_tags_are_known
  validates :thesis_text, length: { maximum: 90 }, allow_blank: true

  def winner?
    market.resolved? && side == market.outcome
  end

  private

  def thesis_tags_are_known
    unknown = Array(thesis_tags) - THESIS_TAGS
    errors.add(:thesis_tags, "contains unknown tags") if unknown.any?
  end
end
