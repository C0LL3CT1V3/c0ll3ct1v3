require "test_helper"

class PointsLedgerEntryTest < ActiveSupport::TestCase
  test "entries cannot be updated or destroyed" do
    user = create_user(handle: "ledger")
    entry = user.points_ledger_entries.signup_bonus.first
    assert_raises(ActiveRecord::ReadOnlyRecord) { entry.update!(amount: 1) }
    assert_raises(ActiveRecord::ReadOnlyRecord) { entry.destroy! }
  end
end
