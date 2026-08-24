ENV["RAILS_ENV"] ||= "test"
require_relative "../config/environment"
require "rails/test_help"

module ActiveSupport
  class TestCase
    parallelize(workers: :number_of_processors)

    def create_user(handle:, email: nil, password: "password123", admin: false)
      User.create!(
        handle: handle,
        email: email || "#{handle}@example.com",
        password: password,
        password_confirmation: password,
        admin: admin
      )
    end

    def create_artist(name: "River Hale")
      Artist.create!(name: name, genre: "indie folk")
    end

    def create_market(artist: nil, question: "Will they play Red Rocks in 2026?")
      Market.create!(
        artist: artist || create_artist,
        question: question,
        kind: :venue_booking,
        resolution_criteria: "Appears on a published Red Rocks lineup or completed setlist for 2026.",
        closes_at: 30.days.from_now
      )
    end
  end
end
