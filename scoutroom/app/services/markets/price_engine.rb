# Pool betting with entry-price weights — not textbook pari-mutuel.
# Quotes include a virtual seed that never pays out. Winners receive their
# stake back plus a share of the real losing pool, weighted by stake / p_entry.
module Markets
  class PriceEngine
    SEED = 100
    P_MIN = 0.05

    Quote = Data.define(:p_yes, :p_no) do
      def for_side(side)
        side.to_sym == :yes ? p_yes : p_no
      end
    end

    Payout = Data.define(:credit, :multiplier)

    def self.quote(real_yes:, real_no:)
      yes_pool = real_yes.to_i + SEED
      no_pool = real_no.to_i + SEED
      p_yes = yes_pool.to_f / (yes_pool + no_pool)
      p_yes = p_yes.clamp(P_MIN, 1.0 - P_MIN)
      Quote.new(p_yes: p_yes, p_no: 1.0 - p_yes)
    end

    # entries: [{side:, points_staked:, implied_probability_at_entry:}, ...]
    # outcome: :yes or :no
    # returns Array of Payout or nil (nil = loser)
    def self.payouts(entries:, outcome:)
      outcome = outcome.to_sym
      raise ArgumentError, "outcome must be yes or no" unless %i[yes no].include?(outcome)

      losing_pool = entries.sum { |entry| entry[:side].to_sym == outcome ? 0 : entry[:points_staked].to_i }

      winner_indexes = []
      raw_bonuses = []

      entries.each_with_index do |entry, index|
        next unless entry[:side].to_sym == outcome

        p = entry[:implied_probability_at_entry].to_f.clamp(P_MIN, 1.0 - P_MIN)
        stake = entry[:points_staked].to_i
        winner_indexes << index
        raw_bonuses << (stake / p)
      end

      bonuses = allocate_integers(raw_bonuses, losing_pool)

      results = Array.new(entries.size)
      winner_indexes.each_with_index do |entry_index, i|
        stake = entries[entry_index][:points_staked].to_i
        credit = stake + bonuses[i]
        results[entry_index] = Payout.new(credit: credit, multiplier: credit.to_f / stake)
      end
      results
    end

    def self.allocate_integers(weights, total)
      return Array.new(weights.size, 0) if weights.empty? || total <= 0

      weight_sum = weights.sum
      exact = weights.map { |w| total * w / weight_sum }
      floors = exact.map(&:floor)
      leftover = total - floors.sum
      remainders = exact.each_with_index.map { |value, i| [ value - floors[i], i ] }
      remainders.sort_by { |remainder, i| [ -remainder, i ] }.first(leftover).each do |_, i|
        floors[i] += 1
      end
      floors
    end
    private_class_method :allocate_integers
  end
end
