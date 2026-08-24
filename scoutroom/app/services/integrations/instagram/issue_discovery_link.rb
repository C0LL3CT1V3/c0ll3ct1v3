module Integrations
  module Instagram
    class IssueDiscoveryLink
      def self.call(market:, comment_id: nil, handle: nil, user: nil)
        DiscoveryLink.create!(
          market: market,
          user: user,
          instagram_comment_id: comment_id,
          instagram_handle: handle,
          token: SecureRandom.urlsafe_base64(24),
          expires_at: 7.days.from_now
        )
      end
    end
  end
end
