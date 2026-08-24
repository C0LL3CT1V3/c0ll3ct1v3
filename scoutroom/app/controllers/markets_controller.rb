class MarketsController < ApplicationController
  def index
    @markets = Market.open.includes(:artist, :predictions).order(:closes_at)
  end

  def show
    @market = Market.includes(:artist, predictions: :user).find(params[:id])
    @quote = @market.quote
    @prediction = current_user&.predictions&.find_by(market: @market)
  end
end
