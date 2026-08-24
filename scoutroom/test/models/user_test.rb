require "test_helper"

class UserTest < ActiveSupport::TestCase
  test "signup bonus credits the ledger and cache" do
    user = create_user(handle: "bonus")
    assert_equal User::SIGNUP_BONUS, user.points_balance_cache
    assert_equal User::SIGNUP_BONUS, user.points_ledger_entries.sum(:amount)
  end
end
