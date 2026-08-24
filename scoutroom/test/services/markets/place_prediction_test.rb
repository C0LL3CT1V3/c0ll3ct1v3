require "test_helper"

class Markets::PlacePredictionTest < ActiveSupport::TestCase
  include ActiveJob::TestHelper

  setup do
    @user = create_user(handle: "scout")
    @market = create_market
  end

  test "locks quote before stake and debits ledger" do
    quote = @market.quote
    assert_enqueued_with(job: Slips::GenerateJob) do
      prediction = Markets::PlacePrediction.call(user: @user, market: @market, side: :yes, points: 50)
      assert_in_delta quote.p_yes, prediction.implied_probability_at_entry, 0.000001
      assert_equal(-50, PointsLedgerEntry.find_by!(reference: prediction, kind: :stake).amount)
    end
    @user.reload
    assert_equal User::SIGNUP_BONUS - 50, @user.points_balance_cache
    assert_equal 1, @user.points_ledger_entries.stake.count
  end

  test "rejects a second call on the same market" do
    Markets::PlacePrediction.call(user: @user, market: @market, side: :yes, points: 10)
    error = assert_raises(Markets::PlacePrediction::Error) do
      Markets::PlacePrediction.call(user: @user, market: @market, side: :no, points: 10)
    end
    assert_match(/already called/i, error.message)
  end

  test "rejects insufficient points" do
    error = assert_raises(Markets::PlacePrediction::Error) do
      Markets::PlacePrediction.call(user: @user, market: @market, side: :yes, points: 50_000)
    end
    assert_match(/enough points/i, error.message)
  end
end
