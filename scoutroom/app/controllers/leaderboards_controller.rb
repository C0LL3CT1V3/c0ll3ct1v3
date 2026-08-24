class LeaderboardsController < ApplicationController
  def show
    @users = User.includes(predictions: [ :market, :slip ]).sort_by { |user|
      -Profiles::Stats.new(user).leaderboard_score
    }.first(50)
  end
end
