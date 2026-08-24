class TipsController < ApplicationController
  before_action :authenticate_user!

  def create
    artist = Artist.find(params[:artist_id])
    _tip, url = Tips::Checkout.call(
      user: current_user,
      artist: artist,
      amount_cents: params[:amount_cents],
      success_url: artist_url(artist, tip: "thanks"),
      cancel_url: artist_url(artist)
    )
    redirect_to url, allow_other_host: true
  rescue Tips::Checkout::Error => e
    redirect_to artist_path(artist), alert: e.message
  end
end
