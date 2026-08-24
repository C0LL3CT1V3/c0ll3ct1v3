class DiscoveryLinksController < ApplicationController
  def show
    link = DiscoveryLink.find_by!(token: params[:token])
    if link.expired?
      redirect_to market_path(link.market), alert: "That invite expired."
      return
    end

    link.update!(redeemed_at: Time.current) unless link.redeemed?
    session[:discovery_link_id] = link.id
    redirect_to market_path(link.market)
  end
end
