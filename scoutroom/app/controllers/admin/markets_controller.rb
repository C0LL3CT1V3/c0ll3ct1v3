module Admin
  class MarketsController < BaseController
    def index
      @markets = Market.includes(:artist).order(closes_at: :desc)
    end

    def new
      @market = Market.new(closes_at: 30.days.from_now)
      @artists = Artist.order(:name)
    end

    def create
      @market = Market.new(market_params)
      if @market.save
        redirect_to admin_markets_path, notice: "Market opened."
      else
        @artists = Artist.order(:name)
        render :new, status: :unprocessable_entity
      end
    end

    def resolve
      market = Market.find(params[:id])
      Markets::ResolveMarket.call(market:, outcome: params[:outcome], note: params[:resolution_note])
      redirect_to admin_markets_path, notice: "Resolution queued."
    rescue Markets::ResolveMarket::Error => e
      redirect_to admin_markets_path, alert: e.message
    end

    private

    def market_params
      params.require(:market).permit(:artist_id, :question, :kind, :resolution_criteria, :closes_at)
    end
  end
end
