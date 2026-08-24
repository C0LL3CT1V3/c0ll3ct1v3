class SlipsController < ApplicationController
  def show
    @slip = Slip.find(params[:id])
    Slips::GenerateJob.perform_now(@slip.prediction_id) unless @slip.image.attached?
  end
end
