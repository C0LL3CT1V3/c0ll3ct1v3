import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static values = { title: String, url: String }

  async share() {
    const payload = { title: this.titleValue, text: this.titleValue, url: this.urlValue }
    if (navigator.share) {
      try {
        await navigator.share(payload)
      } catch (_error) {
        this.copy()
      }
    } else {
      this.copy()
    }
  }

  copy() {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(this.urlValue)
    }
  }
}
