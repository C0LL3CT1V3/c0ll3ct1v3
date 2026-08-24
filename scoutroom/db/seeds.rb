# frozen_string_literal: true

ActiveJob::Base.queue_adapter = :inline

admin = User.find_or_initialize_by(email: "admin@scoutroom.test")
admin.assign_attributes(handle: "admin", password: "password123", password_confirmation: "password123", admin: true)
admin.save!

%w[scout mica juniper].each do |handle|
  User.find_or_create_by!(handle: handle) do |user|
    user.email = "#{handle}@scoutroom.test"
    user.password = "password123"
    user.password_confirmation = "password123"
  end
end

river = Artist.find_or_create_by!(slug: "river-hale") do |artist|
  artist.name = "River Hale"
  artist.genre = "outlaw folk"
  artist.instagram_handle = "riverhale"
end

moth = Artist.find_or_create_by!(slug: "moth-station") do |artist|
  artist.name = "Moth Station"
  artist.genre = "indie rock"
  artist.instagram_handle = "mothstation"
end

june = Artist.find_or_create_by!(slug: "june-voltage") do |artist|
  artist.name = "June Voltage"
  artist.genre = "art pop"
  artist.instagram_handle = "junevoltage"
end

red_rocks = Market.find_or_create_by!(question: "Will River Hale play Red Rocks in 2026?") do |market|
  market.artist = river
  market.kind = :venue_booking
  market.resolution_criteria = "A dated 2026 Red Rocks listing, announcement, or completed setlist. Admin-resolved; no auto-sync."
  market.closes_at = Time.zone.parse("2026-12-15 23:59:59")
end

followers = Market.find_or_create_by!(question: "Will Moth Station cross 50,000 Spotify followers in 2026?") do |market|
  market.artist = moth
  market.kind = :listener_threshold
  market.resolution_criteria = "Spotify artist page follower count (public API) or a screenshot at year end. Monthly listeners are not used."
  market.closes_at = Time.zone.parse("2026-12-31 23:59:59")
end

Market.find_or_create_by!(question: "Will June Voltage release a full-length in 2026?") do |market|
  market.artist = june
  market.kind = :other
  market.resolution_criteria = "A full-length appears on streaming stores or Bandcamp with a 2026 release date."
  market.closes_at = Time.zone.parse("2026-12-31 23:59:59")
end

scout = User.find_by!(handle: "scout")
mica = User.find_by!(handle: "mica")
juniper = User.find_by!(handle: "juniper")

unless scout.predictions.exists?(market: red_rocks)
  Markets::PlacePrediction.call(user: scout, market: red_rocks, side: :yes, points: 80, thesis_tags: %w[live_show_energy], thesis_text: "Front range rooms already oversell.")
end
unless mica.predictions.exists?(market: red_rocks)
  Markets::PlacePrediction.call(user: mica, market: red_rocks, side: :yes, points: 40, thesis_tags: %w[fanbase_growth])
end
unless juniper.predictions.exists?(market: followers)
  Markets::PlacePrediction.call(user: juniper, market: followers, side: :yes, points: 60, thesis_tags: %w[playlist_momentum], thesis_text: "College radio is stacking the single.")
end

puts "Seeded Scoutroom. Admin login: admin@scoutroom.test / password123"
