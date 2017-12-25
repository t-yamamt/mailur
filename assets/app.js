import Vue from 'vue';
import './tags.js';
import './msg.js';
import './msgs.js';
import './thread.js';
import tpl from './app.html';

Vue.component('app', {
  template: tpl,
  data: function() {
    return {
      tags: window.data.tags,
      query: null,
      addrs: [],
      picSize: 20,
      split: false,
      bigger: false
    };
  },
  created: function() {
    window.app = this;

    let q = decodeURIComponent(location.hash.slice(1));
    if (!q) {
      q = ':threads keyword #inbox';
      window.location.hash = q;
    }
    this.query = q;
  },
  computed: {
    allTags: function() {
      let tags = [];
      for (let i in this.tags) {
        let tag = this.tags[i];
        if (tag.unread || tag.pinned) {
          tags.push(i);
        }
      }
      return tags;
    }
  },
  watch: {
    query: function(val) {
      window.location.hash = val;
    }
  },
  methods: {
    fetch: function(q) {
      return this.$refs.main.fetch(q);
    },
    pics: function(msgs) {
      let hashes = [];
      for (let m in msgs) {
        for (let f of msgs[m].from_list) {
          if (
            f.hash &&
            hashes.indexOf(f.hash) == -1 &&
            this.addrs.indexOf(f.hash) == -1
          ) {
            hashes.push(f.hash);
          }
        }
      }
      if (hashes.length == 0) {
        return;
      }
      this.addrs = this.addrs.concat(hashes);
      while (hashes.length > 0) {
        let sheet = document.createElement('link');
        let few = encodeURIComponent(hashes.splice(0, 50));
        sheet.href = `/avatars.css?size=${this.picSize}&hashes=${few}`;
        sheet.rel = 'stylesheet';
        document.body.appendChild(sheet);
      }
    },
    openInSplit: function(query) {
      this.split = true;
      this.$nextTick(() => {
        this.$refs.split.fetch(query);
      });
      return;
    },
    toggleSplit: function() {
      this.split = !this.split;
      this.$nextTick(() => {
        if (this.split) {
          this.$refs.split.fetch(this.query);
        }
      });
    },
    toggleBigger: function() {
      this.bigger = !this.bigger;
    },
    logout: function() {
      window.location = '/logout';
    }
  }
});

new Vue({
  el: '#app',
  template: '<app />'
});