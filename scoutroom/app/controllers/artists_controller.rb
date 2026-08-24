class ArtistsController < ApplicationController
  def show
    @artist = Artist.find(params[:id])
    @markets = @artist.markets.includes(:predictions).order(closes_at: :desc)
    @believers = User.joins(predictions: :market)
                     .where(markets: { artist_id: @artist.id }, predictions: { side: :yes })
                     .distinct
                     .limit(24)
  end
end
