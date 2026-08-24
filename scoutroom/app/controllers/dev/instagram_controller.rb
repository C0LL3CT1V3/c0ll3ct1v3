module Dev
  class InstagramController < ApplicationController
    def new
      @markets = Market.open.includes(:artist)
    end

    def comment
      market = Market.find(params[:market_id])
      link = Integrations::Instagram::IssueDiscoveryLink.call(
        market: market,
        comment_id: SecureRandom.hex(8),
        handle: params[:handle]
      )
      Integrations::Instagram::SendDiscoveryLinkJob.perform_later(link.id)
      @url = discovery_link_url(link.token)
      @link = link
      render :show
    end
  end
end
