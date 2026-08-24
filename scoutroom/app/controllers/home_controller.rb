class HomeController < ApplicationController
  def index
    @markets = Market.open.includes(:artist, :predictions).order(:closes_at)
    @leaderboard = ranked_users.first(5)
  end

  private

  def ranked_users
    User.includes(predictions: :market).sort_by { |user| -Profiles::Stats.new(user).leaderboard_score }
  end
end
