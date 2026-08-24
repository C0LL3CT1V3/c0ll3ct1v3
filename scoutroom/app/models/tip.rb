class Tip < ApplicationRecord
  STATUSES = %w[pending succeeded failed].freeze

  belongs_to :user
  belongs_to :artist

  enum :status, STATUSES.index_by(&:itself), validate: true, default: :pending

  validates :amount_cents, numericality: { only_integer: true, greater_than: 0 }
end
