class DiscoveryLink < ApplicationRecord
  belongs_to :market
  belongs_to :user, optional: true

  validates :token, presence: true, uniqueness: true
  validates :expires_at, presence: true

  def expired?
    expires_at.past?
  end

  def redeemed?
    redeemed_at.present?
  end
end
