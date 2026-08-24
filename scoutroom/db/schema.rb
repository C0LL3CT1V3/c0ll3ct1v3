# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.0].define(version: 2026_08_21_150000) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "pg_catalog.plpgsql"

  create_table "active_storage_attachments", force: :cascade do |t|
    t.string "name", null: false
    t.string "record_type", null: false
    t.bigint "record_id", null: false
    t.bigint "blob_id", null: false
    t.datetime "created_at", null: false
    t.index ["blob_id"], name: "index_active_storage_attachments_on_blob_id"
    t.index ["record_type", "record_id", "name", "blob_id"], name: "index_active_storage_attachments_uniqueness", unique: true
  end

  create_table "active_storage_blobs", force: :cascade do |t|
    t.string "key", null: false
    t.string "filename", null: false
    t.string "content_type"
    t.text "metadata"
    t.string "service_name", null: false
    t.bigint "byte_size", null: false
    t.string "checksum"
    t.datetime "created_at", null: false
    t.index ["key"], name: "index_active_storage_blobs_on_key", unique: true
  end

  create_table "active_storage_variant_records", force: :cascade do |t|
    t.bigint "blob_id", null: false
    t.string "variation_digest", null: false
    t.index ["blob_id", "variation_digest"], name: "index_active_storage_variant_records_uniqueness", unique: true
  end

  create_table "artists", force: :cascade do |t|
    t.string "name", null: false
    t.string "slug", null: false
    t.string "spotify_id"
    t.string "instagram_handle"
    t.string "genre"
    t.string "image_url"
    t.string "stripe_account_id"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["slug"], name: "index_artists_on_slug", unique: true
    t.index ["spotify_id"], name: "index_artists_on_spotify_id", unique: true, where: "(spotify_id IS NOT NULL)"
  end

  create_table "discovery_links", force: :cascade do |t|
    t.string "token", null: false
    t.bigint "market_id", null: false
    t.bigint "user_id"
    t.string "instagram_comment_id"
    t.string "instagram_handle"
    t.datetime "expires_at", null: false
    t.datetime "redeemed_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["market_id"], name: "index_discovery_links_on_market_id"
    t.index ["token"], name: "index_discovery_links_on_token", unique: true
    t.index ["user_id"], name: "index_discovery_links_on_user_id"
  end

  create_table "markets", force: :cascade do |t|
    t.bigint "artist_id", null: false
    t.string "question", null: false
    t.string "kind", default: "other", null: false
    t.text "resolution_criteria", null: false
    t.datetime "closes_at", null: false
    t.datetime "resolved_at"
    t.string "outcome", default: "pending", null: false
    t.text "resolution_note"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["artist_id"], name: "index_markets_on_artist_id"
    t.index ["closes_at"], name: "index_markets_on_closes_at"
    t.index ["outcome"], name: "index_markets_on_outcome"
  end

  create_table "points_ledger_entries", force: :cascade do |t|
    t.bigint "user_id", null: false
    t.integer "amount", null: false
    t.string "kind", null: false
    t.string "reference_type"
    t.bigint "reference_id"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["kind"], name: "index_points_ledger_entries_on_kind"
    t.index ["reference_type", "reference_id"], name: "index_points_ledger_entries_on_reference_type_and_reference_id"
    t.index ["user_id"], name: "index_points_ledger_entries_on_user_id"
  end

  create_table "predictions", force: :cascade do |t|
    t.bigint "user_id", null: false
    t.bigint "market_id", null: false
    t.string "side", null: false
    t.integer "points_staked", null: false
    t.decimal "implied_probability_at_entry", precision: 8, scale: 6, null: false
    t.decimal "payout_multiplier", precision: 12, scale: 6
    t.jsonb "thesis_tags", default: [], null: false
    t.string "thesis_text"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["market_id"], name: "index_predictions_on_market_id"
    t.index ["side"], name: "index_predictions_on_side"
    t.index ["user_id", "market_id"], name: "index_predictions_on_user_id_and_market_id", unique: true
    t.index ["user_id"], name: "index_predictions_on_user_id"
  end

  create_table "slips", force: :cascade do |t|
    t.bigint "prediction_id", null: false
    t.string "seed", null: false
    t.decimal "discovery_percentile", precision: 8, scale: 6, default: "0.0", null: false
    t.jsonb "thesis_tags", default: [], null: false
    t.string "thesis_text"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["prediction_id"], name: "index_slips_on_prediction_id", unique: true
    t.index ["seed"], name: "index_slips_on_seed", unique: true
  end

  create_table "tips", force: :cascade do |t|
    t.bigint "user_id", null: false
    t.bigint "artist_id", null: false
    t.integer "amount_cents", null: false
    t.string "stripe_payment_intent_id"
    t.string "status", default: "pending", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["artist_id"], name: "index_tips_on_artist_id"
    t.index ["stripe_payment_intent_id"], name: "index_tips_on_stripe_payment_intent_id", unique: true, where: "(stripe_payment_intent_id IS NOT NULL)"
    t.index ["user_id"], name: "index_tips_on_user_id"
  end

  create_table "users", force: :cascade do |t|
    t.string "email", default: "", null: false
    t.string "encrypted_password", default: "", null: false
    t.string "reset_password_token"
    t.datetime "reset_password_sent_at"
    t.datetime "remember_created_at"
    t.string "handle", null: false
    t.boolean "admin", default: false, null: false
    t.integer "points_balance_cache", default: 0, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["email"], name: "index_users_on_email", unique: true
    t.index ["handle"], name: "index_users_on_handle", unique: true
    t.index ["reset_password_token"], name: "index_users_on_reset_password_token", unique: true
  end

  add_foreign_key "active_storage_attachments", "active_storage_blobs", column: "blob_id"
  add_foreign_key "active_storage_variant_records", "active_storage_blobs", column: "blob_id"
  add_foreign_key "discovery_links", "markets"
  add_foreign_key "discovery_links", "users"
  add_foreign_key "markets", "artists"
  add_foreign_key "points_ledger_entries", "users"
  add_foreign_key "predictions", "markets"
  add_foreign_key "predictions", "users"
  add_foreign_key "slips", "predictions"
  add_foreign_key "tips", "artists"
  add_foreign_key "tips", "users"
end
