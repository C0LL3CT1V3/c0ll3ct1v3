require "test_helper"

class Markets::PriceEngineTest < ActiveSupport::TestCase
  test "empty market quotes fifty percent" do
    quote = Markets::PriceEngine.quote(real_yes: 0, real_no: 0)
    assert_in_delta 0.5, quote.p_yes, 0.0001
    assert_in_delta 0.5, quote.p_no, 0.0001
  end

  test "yes money raises yes probability" do
    quote = Markets::PriceEngine.quote(real_yes: 100, real_no: 0)
    assert_operator quote.p_yes, :>, 0.5
    assert_in_delta 200.0 / 300.0, quote.p_yes, 0.0001
  end

  test "probability is clamped" do
    quote = Markets::PriceEngine.quote(real_yes: 100_000, real_no: 0)
    assert_in_delta 0.95, quote.p_yes, 0.0001
    assert_in_delta 0.05, quote.p_no, 0.0001
  end

  test "winners receive stake plus losing pool and points are conserved" do
    entries = [
      { side: :yes, points_staked: 10, implied_probability_at_entry: 0.5 },
      { side: :no, points_staked: 30, implied_probability_at_entry: 0.5 }
    ]
    payouts = Markets::PriceEngine.payouts(entries: entries, outcome: :yes)
    assert_equal 40, payouts[0].credit
    assert_nil payouts[1]
    assert_in_delta 4.0, payouts[0].multiplier, 0.0001
  end

  test "early low probability wins more of the losing pool than late consensus" do
    entries = [
      { side: :yes, points_staked: 10, implied_probability_at_entry: 0.2 },
      { side: :yes, points_staked: 10, implied_probability_at_entry: 0.8 },
      { side: :no, points_staked: 20, implied_probability_at_entry: 0.5 }
    ]
    payouts = Markets::PriceEngine.payouts(entries: entries, outcome: :yes)
    assert_operator payouts[0].credit, :>, payouts[1].credit
    assert_equal 40, payouts[0].credit + payouts[1].credit
  end

  test "all-yes market returns stakes only" do
    entries = [
      { side: :yes, points_staked: 15, implied_probability_at_entry: 0.5 },
      { side: :yes, points_staked: 25, implied_probability_at_entry: 0.6 }
    ]
    payouts = Markets::PriceEngine.payouts(entries: entries, outcome: :yes)
    assert_equal 15, payouts[0].credit
    assert_equal 25, payouts[1].credit
  end
end
