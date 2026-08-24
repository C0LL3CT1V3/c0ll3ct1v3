module Admin
  class BaseController < ApplicationController
    before_action :authenticate_user!
    before_action :require_admin!
  end
end
