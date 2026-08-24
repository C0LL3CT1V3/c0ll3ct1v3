class Slip < ApplicationRecord
  belongs_to :prediction
  has_one_attached :image

  validates :seed, presence: true, uniqueness: true
  validates :discovery_percentile, numericality: { greater_than_or_equal_to: 0, less_than_or_equal_to: 1 }

  def artist
    prediction.market.artist
  end
end
