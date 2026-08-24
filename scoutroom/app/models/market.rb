class Market < ApplicationRecord
  KINDS = %w[venue_booking listener_threshold other].freeze
  OUTCOMES = %w[pending yes no void].freeze

  belongs_to :artist
  has_many :predictions, dependent: :restrict_with_exception
  has_many :discovery_links, dependent: :destroy

  enum :kind, KINDS.index_by(&:itself), validate: true
  enum :outcome, OUTCOMES.index_by(&:itself), validate: true, default: :pending

  validates :question, :resolution_criteria, :closes_at, presence: true

  scope :open, -> { pending.where("closes_at > ?", Time.current) }
  scope :resolved, -> { where(outcome: %w[yes no]) }
  scope :closed_for_entry, -> { where("closes_at <= ?", Time.current) }

  def open_for_entry?
    pending? && closes_at.future?
  end

  def resolved?
    yes? || no?
  end

  def real_yes_points
    predictions.yes.sum(:points_staked)
  end

  def real_no_points
    predictions.no.sum(:points_staked)
  end

  def quote
    Markets::PriceEngine.quote(real_yes: real_yes_points, real_no: real_no_points)
  end

  def believer_count
    predictions.yes.count
  end
end
