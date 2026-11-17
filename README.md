# moniquemartin.net

Static copy of moniquemartin.net (formerly WordPress on HostGator), hosted free on Cloudflare Pages.

- Pages: `src/index.html` (home), `src/mintyfresh/index.html`, `src/bio/index.html`. They are the old site's HTML with WordPress, donation, Twitter and tracking scripts removed, so the design matches the old site exactly.
- Images, styles and scripts from the old site live under `src/wp-content`, `src/wp-includes` and `src/fonts`.
- Old `?page_id=` links still work (the home page forwards them).
- Build: `npm run build` (Eleventy), output `_site`.
- Cloudflare Pages settings: Framework preset None, build command `npm run build`, output directory `_site`, root directory empty.
- Edit online with [Pages CMS](https://app.pagescms.org) (GitHub login).
- `scripts/import-old-site.py` is the one-time script that produced the pages from the snapshot on the `old-site-snapshot` branch.
