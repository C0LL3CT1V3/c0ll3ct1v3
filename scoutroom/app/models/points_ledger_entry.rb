class PointsLedgerEntry < ApplicationRecord
  KINDS = %w[signup_bonus stake payout refund admin_adjustment].freeze

  belongs_to :user
  belongs_to :reference, polymorphic: true, optional: true

  enum :kind, KINDS.index_by(&:itself), validate: true

  validates :amount, numericality: { other_than: 0, only_integer: true }

  before_update { raise ActiveRecord::ReadOnlyRecord, "ledger entries are immutable" }
  before_destroy { raise ActiveRecord::ReadOnlyRecord, "ledger entries are immutable" }
end
