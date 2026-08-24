class CreateScoutroomTables < ActiveRecord::Migration[8.0]
  def change
    create_table :artists do |t|
      t.string :name, null: false
      t.string :slug, null: false
      t.string :spotify_id
      t.string :instagram_handle
      t.string :genre
      t.string :image_url
      t.string :stripe_account_id
      t.timestamps
    end
    add_index :artists, :slug, unique: true
    add_index :artists, :spotify_id, unique: true, where: "spotify_id IS NOT NULL"

    create_table :markets do |t|
      t.references :artist, null: false, foreign_key: true
      t.string :question, null: false
      t.string :kind, null: false, default: "other"
      t.text :resolution_criteria, null: false
      t.datetime :closes_at, null: false
      t.datetime :resolved_at
      t.string :outcome, null: false, default: "pending"
      t.text :resolution_note
      t.timestamps
    end
    add_index :markets, :outcome
    add_index :markets, :closes_at

    create_table :predictions do |t|
      t.references :user, null: false, foreign_key: true
      t.references :market, null: false, foreign_key: true
      t.string :side, null: false
      t.integer :points_staked, null: false
      t.decimal :implied_probability_at_entry, precision: 8, scale: 6, null: false
      t.decimal :payout_multiplier, precision: 12, scale: 6
      t.jsonb :thesis_tags, null: false, default: []
      t.string :thesis_text
      t.timestamps
    end
    add_index :predictions, [ :user_id, :market_id ], unique: true
    add_index :predictions, :side

    create_table :points_ledger_entries do |t|
      t.references :user, null: false, foreign_key: true
      t.integer :amount, null: false
      t.string :kind, null: false
      t.string :reference_type
      t.bigint :reference_id
      t.timestamps
    end
    add_index :points_ledger_entries, [ :reference_type, :reference_id ]
    add_index :points_ledger_entries, :kind

    create_table :tips do |t|
      t.references :user, null: false, foreign_key: true
      t.references :artist, null: false, foreign_key: true
      t.integer :amount_cents, null: false
      t.string :stripe_payment_intent_id
      t.string :status, null: false, default: "pending"
      t.timestamps
    end
    add_index :tips, :stripe_payment_intent_id, unique: true, where: "stripe_payment_intent_id IS NOT NULL"

    create_table :slips do |t|
      t.references :prediction, null: false, foreign_key: true, index: { unique: true }
      t.string :seed, null: false
      t.decimal :discovery_percentile, precision: 8, scale: 6, null: false, default: 0
      t.jsonb :thesis_tags, null: false, default: []
      t.string :thesis_text
      t.timestamps
    end
    add_index :slips, :seed, unique: true

    create_table :discovery_links do |t|
      t.string :token, null: false
      t.references :market, null: false, foreign_key: true
      t.references :user, foreign_key: true
      t.string :instagram_comment_id
      t.string :instagram_handle
      t.datetime :expires_at, null: false
      t.datetime :redeemed_at
      t.timestamps
    end
    add_index :discovery_links, :token, unique: true
  end
end
