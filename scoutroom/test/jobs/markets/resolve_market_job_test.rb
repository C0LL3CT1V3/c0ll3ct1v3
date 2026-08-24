require "test_helper"

class Markets::ResolveMarketJobTest < ActiveSupport::TestCase
  include ActiveJob::TestHelper

  test "pays winners and refunds void markets" do
    yes_user = create_user(handle: "early")
    no_user = create_user(handle: "fade")
    market = create_market

    Markets::PlacePrediction.call(user: yes_user, market: market, side: :yes, points: 20)
    Markets::PlacePrediction.call(user: no_user, market: market, side: :no, points: 80)

    perform_enqueued_jobs do
      Markets::ResolveMarket.call(market: market, outcome: :yes, note: "Announced.")
    end

    yes_user.reload
    no_user.reload
    assert_equal User::SIGNUP_BONUS + 80, yes_user.points_balance_cache
    assert_equal User::SIGNUP_BONUS - 80, no_user.points_balance_cache
    assert_equal "yes", market.reload.outcome
  end

  test "void refunds every stake" do
    user = create_user(handle: "voided")
    market = create_market
    Markets::PlacePrediction.call(user: user, market: market, side: :yes, points: 40)

    perform_enqueued_jobs do
      Markets::ResolveMarket.call(market: market, outcome: :void)
    end

    assert_equal User::SIGNUP_BONUS, user.reload.points_balance_cache
    assert_equal "void", market.reload.outcome
  end
end
