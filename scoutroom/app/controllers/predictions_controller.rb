class PredictionsController < ApplicationController
  before_action :authenticate_user!

  def create
    market = Market.find(params[:market_id])
    prediction = Markets::PlacePrediction.call(
      user: current_user,
      market: market,
      side: params[:side],
      points: params[:points],
      thesis_tags: Array(params[:thesis_tags]),
      thesis_text: params[:thesis_text]
    )
    redirect_to market_path(market), notice: "Call locked. Your slip is printing."
  rescue Markets::PlacePrediction::Error => e
    redirect_to market_path(market), alert: e.message
  end
end
