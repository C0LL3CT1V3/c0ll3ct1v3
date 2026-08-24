class Artist < ApplicationRecord
  has_many :markets, dependent: :destroy
  has_many :tips, dependent: :restrict_with_exception

  validates :name, :slug, presence: true
  validates :slug, uniqueness: true

  before_validation :ensure_slug

  def to_param
    slug
  end

  def tips_enabled?
    stripe_account_id.present? && ENV["STRIPE_SECRET_KEY"].present?
  end

  def lifetime_tips_cents
    tips.succeeded.sum(:amount_cents)
  end

  private

  def ensure_slug
    self.slug = name.to_s.parameterize if slug.blank?
  end
end
