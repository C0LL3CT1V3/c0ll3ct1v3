module Integrations
  module Instagram
    class SendDiscoveryLinkJob < ApplicationJob
      queue_as :default

      def perform(discovery_link_id)
        link = DiscoveryLink.find(discovery_link_id)
        url = Rails.application.routes.url_helpers.discovery_link_url(
          link.token,
          **Rails.application.config.action_mailer.default_url_options
        )
        Rails.logger.info("[instagram.mock] DM #{link.instagram_handle || 'unknown'}: #{url}")
        url
      end
    end
  end
end
