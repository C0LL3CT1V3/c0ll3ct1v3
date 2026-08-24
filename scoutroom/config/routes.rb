require "sidekiq/web"

Rails.application.routes.draw do
  devise_for :users
  root "home#index"

  resources :markets, only: %i[index show] do
    resources :predictions, only: :create
  end
  resources :slips, only: :show
  resources :artists, only: :show do
    resources :tips, only: :create
  end
  get "leaderboard", to: "leaderboards#show", as: :leaderboard
  get "u/:handle", to: "profiles#show", as: :profile
  get "r/:token", to: "discovery_links#show", as: :discovery_link
  post "stripe/webhook", to: "stripe_webhooks#create"

  namespace :admin do
    resources :markets, only: %i[index new create] do
      post :resolve, on: :member
    end
  end

  if Rails.env.development?
    namespace :dev do
      get "ig", to: "instagram#new"
      post "ig/comment", to: "instagram#comment"
    end
    mount Sidekiq::Web => "/sidekiq"
  end

  get "up" => "rails/health#show", as: :rails_health_check
end
