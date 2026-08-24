class PointsLedger
  class InsufficientPoints < StandardError; end

  def self.record!(user:, amount:, kind:, reference: nil)
    user.with_lock do
      if amount.negative? && user.points_balance_cache + amount < 0
        raise InsufficientPoints, "not enough points"
      end

      entry = user.points_ledger_entries.create!(
        amount: amount,
        kind: kind,
        reference: reference
      )
      user.increment!(:points_balance_cache, amount)
      entry
    end
  end
end
