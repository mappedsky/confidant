:layout: landing
:hide_breadcrumbs: true
:hide_ai_links: true
:content_max_width: 1240px
:description: Confidant stores versioned secrets in DynamoDB, encrypts them with AWS KMS, and only returns the secrets mapped to each service or group.

Confidant
=========

.. raw:: html

   <div class="splash-bleed">
   <section class="splash-hero-wrap">
     <div class="splash-hero splash-hero-telegram">
       <div class="splash-bg-grid" aria-hidden="true"></div>

       <div class="splash-overhead" aria-hidden="true">
         <div class="splash-overhead-pigeon">
           <svg viewBox="0 0 96 72" aria-hidden="true">
             <path d="M 6 34 L 22 30 L 24 40 L 22 46 L 8 44 Z" fill="currentColor" opacity=".75"/>
             <path d="M 20 28 Q 30 18 50 22 Q 70 26 68 42 Q 64 54 44 54 Q 24 54 18 44 Q 14 36 20 28 Z" fill="currentColor"/>
             <path d="M 56 24 Q 70 14 80 18 Q 86 22 82 30 Q 78 36 68 34 Q 60 32 56 30 Z" fill="currentColor"/>
             <path d="M 78 16 Q 80 12 84 14 Q 83 18 80 19 Z" fill="currentColor" opacity=".85"/>
             <path d="M 84 22 L 92 23 L 84 26 Z" fill="currentColor" opacity=".9"/>
             <circle cx="78" cy="23" r="2.4" fill="var(--splash-bg-elev)"/>
             <circle cx="78" cy="23" r="1.1" fill="currentColor"/>
             <g class="splash-wing">
               <path d="M 34 26 Q 42 10 60 18 Q 58 30 46 34 Q 36 34 34 26 Z" fill="currentColor" opacity=".92"/>
             </g>
             <path d="M 44 54 L 44 62" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" fill="none"/>
             <path d="M 50 54 L 50 62" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" fill="none"/>
             <rect x="42.5" y="57" width="3" height="2.5" fill="var(--splash-accent)"/>
           </svg>
         </div>
       </div>

       <div class="splash-eyebrow"><span>open source &middot; secret management</span></div>
       <h1 class="splash-h1">Secrets, kept <em>/* in confidence */</em> and shipped on demand.</h1>
       <p class="splash-lede">A secret manager for services and teams. Store versioned secrets in DynamoDB, encrypt them with AWS&nbsp;KMS, and map each one to exactly the group that should see it.</p>
       <div class="splash-cta-row">
         <a class="splash-btn splash-btn-primary" href="contents.html">Read the docs &rarr;</a>
         <a class="splash-btn" href="https://github.com/mappedsky/confidant">
           <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.1c-3.3.7-4-1.6-4-1.6-.5-1.4-1.3-1.8-1.3-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.9 2.9 1.3 3.6 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-6 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.3 18.3 4.6 18.3 4.6c.7 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.7-2.8 5.7-5.5 6 .4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3z"/></svg>
           GitHub
         </a>
       </div>

       <div class="splash-tape" aria-hidden="true">
         <div class="splash-tape-track">
           <span>AWS KMS &middot; envelope encryption</span>
           <span>DynamoDB-backed storage</span>
           <span>Versioned secrets &middot; rollback anywhere</span>
           <span>IAM-authenticated service auth</span>
           <span>Groups map secrets to services</span>
           <span>Web UI for operators</span>
           <span>Audit trail included</span>
           <span>AWS KMS &middot; envelope encryption</span>
           <span>DynamoDB-backed storage</span>
           <span>Versioned secrets &middot; rollback anywhere</span>
           <span>IAM-authenticated service auth</span>
           <span>Groups map secrets to services</span>
           <span>Web UI for operators</span>
           <span>Audit trail included</span>
         </div>
       </div>
     </div>
   </section>

   <section class="splash-section" id="features">
     <div class="splash-section-head">
       <div>
         <div class="splash-eyebrow"><span>what's inside</span></div>
         <h2>Six pieces. One quiet, versioned secret pipeline.</h2>
       </div>
       <p>Confidant pairs an opinionated storage model with AWS primitives so the operational surface is small and the security model easy to reason about.</p>
     </div>
     <div class="splash-features">
       <div class="splash-feature splash-feature-accent">
         <div class="splash-feature-num">01 / ENCRYPTION</div>
         <svg class="splash-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/><circle cx="12" cy="15.5" r="1.4" fill="currentColor"/></svg>
         <h3>AWS KMS at rest</h3>
         <p>Every secret is wrapped with an envelope key issued by AWS&nbsp;KMS. Ciphertext is the only thing that ever lands on disk.</p>
       </div>
       <div class="splash-feature">
         <div class="splash-feature-num">02 / STORAGE</div>
         <svg class="splash-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="5.5" rx="8" ry="2.5"/><path d="M4 5.5v6c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5v-6"/><path d="M4 11.5v6c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5v-6"/></svg>
         <h3>DynamoDB-backed</h3>
         <p>Secrets, revisions, groups and mappings all live in DynamoDB. No extra infra to stand up; scale comes for free.</p>
       </div>
       <div class="splash-feature">
         <div class="splash-feature-num">03 / VERSIONING</div>
         <svg class="splash-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="6" cy="6" r="2.3"/><circle cx="6" cy="18" r="2.3"/><circle cx="18" cy="12" r="2.3"/><path d="M6 8.3v7.4M7.8 6.5A6 6 0 0 1 15.7 12M15.7 12A6 6 0 0 1 7.8 17.5"/></svg>
         <h3>Versioned, not overwritten</h3>
         <p>Every write mints a new revision. Roll a service back to any previous secret without hunting through backups.</p>
       </div>
       <div class="splash-feature">
         <div class="splash-feature-num">04 / MAPPING</div>
         <svg class="splash-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="5" cy="12" r="2.3"/><circle cx="19" cy="5.5" r="2.3"/><circle cx="19" cy="18.5" r="2.3"/><path d="M7.1 11l9.7-4.6M7.1 13l9.7 4.6"/></svg>
         <h3>Groups map to services</h3>
         <p>Define user-facing groups once; each service reads only the secrets its group is authorized for. No bespoke policy per app.</p>
       </div>
       <div class="splash-feature">
         <div class="splash-feature-num">05 / OPERATOR UI</div>
         <svg class="splash-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 9h18M7 14h6"/></svg>
         <h3>Operator web UI</h3>
         <p>Manage secrets, groups and mappings from a single console. Purpose-built for the humans rotating the keys, not just the services consuming them.</p>
       </div>
       <div class="splash-feature">
         <div class="splash-feature-num">06 / IAM AUTH</div>
         <svg class="splash-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l8 3v5a9 9 0 0 1-8 9 9 9 0 0 1-8-9V6l8-3z"/><path d="M9.5 12l2 2 3.5-4"/></svg>
         <h3>Service auth via IAM</h3>
         <p>Services authenticate with AWS&nbsp;IAM credentials they already have. No separate identity system to issue, rotate, or leak.</p>
       </div>
     </div>
   </section>

   <section class="splash-cta-band">
     <div class="splash-cta-inner">
       <div>
         <div class="splash-eyebrow"><span>get started</span></div>
         <h2>Open the docs, or read the source.</h2>
         <p>Confidant is an open-source project &mdash; the handbook and the implementation are the same distance away.</p>
       </div>
       <div class="splash-links-card">
         <a class="splash-link-row" href="contents.html">
           <span class="splash-ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h10l4 4v12H4z"/><path d="M14 4v4h4M8 13h8M8 17h6"/></svg></span>
           <span class="splash-tx"><span class="splash-tx-t">Documentation</span><span class="splash-tx-s">handbook, API, and ops guides</span></span>
           <span class="splash-arr">&rarr;</span>
         </a>
         <a class="splash-link-row" href="https://github.com/mappedsky/confidant">
           <span class="splash-ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.1c-3.3.7-4-1.6-4-1.6-.5-1.4-1.3-1.8-1.3-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.9 2.9 1.3 3.6 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-6 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.3 18.3 4.6 18.3 4.6c.7 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.7-2.8 5.7-5.5 6 .4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3z"/></svg></span>
           <span class="splash-tx"><span class="splash-tx-t">Source on GitHub</span><span class="splash-tx-s">mappedsky/confidant</span></span>
           <span class="splash-arr">&rarr;</span>
         </a>
         <a class="splash-link-row" href="install.html">
           <span class="splash-ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 17l4-4 4 4 8-8"/><path d="M14 5h6v6"/></svg></span>
           <span class="splash-tx"><span class="splash-tx-t">Install guide</span><span class="splash-tx-s">pip &middot; docker &middot; terraform</span></span>
           <span class="splash-arr">&rarr;</span>
         </a>
       </div>
     </div>
   </section>
   </div>

.. toctree::
   :hidden:

   contents
