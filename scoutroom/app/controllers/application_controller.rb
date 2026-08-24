class ApplicationController < ActionController::Base
  before_action :configure_permitted_parameters, if: :devise_controller?

  helper_method :admin?

  def after_sign_in_path_for(_resource)
    root_path
  end

  private

  def configure_permitted_parameters
    devise_parameter_sanitizer.permit(:sign_up, keys: [ :handle ])
    devise_parameter_sanitizer.permit(:account_update, keys: [ :handle ])
  end

  def admin?
    user_signed_in? && current_user.admin?
  end

  def require_admin!
    unless admin?
      redirect_to root_path, alert: "Not authorized."
    end
  end
end
