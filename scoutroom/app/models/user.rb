class User < ApplicationRecord
  SIGNUP_BONUS = 1_000

  devise :database_authenticatable, :registerable,
         :recoverable, :rememberable, :validatable

  has_many :predictions, dependent: :restrict_with_exception
  has_many :points_ledger_entries, dependent: :restrict_with_exception
  has_many :tips, dependent: :restrict_with_exception
  has_many :discovery_links, dependent: :nullify

  validates :handle, presence: true, uniqueness: { case_sensitive: false },
                     length: { in: 2..20 },
                     format: { with: /\A[a-z0-9_]+\z/i, message: "letters, numbers, and underscores only" }

  before_validation :normalize_handle
  after_create :grant_signup_bonus

  def to_param
    handle
  end

  def points_balance
    points_balance_cache
  end

  def reconcile_points!
    update!(points_balance_cache: points_ledger_entries.sum(:amount))
  end

  def accuracy
    resolved = predictions.joins(:market).merge(Market.resolved)
    return 0.0 if resolved.none?

    wins = resolved.select { |p| p.side == p.market.outcome }.size
    wins.to_f / resolved.size
  end

  def conviction
    winners = predictions.joins(:market).merge(Market.resolved).select { |p| p.side == p.market.outcome }
    return 0.0 if winners.empty?

    winners.sum { |p| 1.0 / p.implied_probability_at_entry.to_f } / winners.size
  end

  private

  def normalize_handle
    self.handle = handle.to_s.strip.downcase
  end

  def grant_signup_bonus
    return if points_ledger_entries.exists?

    PointsLedger.record!(user: self, amount: SIGNUP_BONUS, kind: :signup_bonus)
  end
end
