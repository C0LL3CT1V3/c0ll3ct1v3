class ProfilesController < ApplicationController
  def show
    @user = User.find_by!(handle: params[:handle])
    @stats = Profiles::Stats.new(@user)
    @predictions = @user.predictions.includes(:slip, market: :artist).order(created_at: :desc)
  end
end
