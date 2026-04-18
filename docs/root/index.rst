:layout: landing
:hide_breadcrumbs: true
:hide_ai_links: true
:content_max_width: 1120px
:description: Confidant stores secrets in DynamoDB, encrypts them with AWS KMS, and only returns the secrets mapped to each service or group.

Confidant
=========

.. container:: hero-shell

   .. container:: hero-copy

      Secret management for services and teams.

      Confidant stores versioned secrets in DynamoDB, encrypts them with
      AWS KMS, and only returns the secrets mapped to each service or group.

      .. container:: buttons

         :doc:`Docs <contents>`
         `GitHub <https://github.com/mappedsky/confidant>`_

      * User-defined groups map secrets to the services that should see them.
      * Secrets stay encrypted at rest with AWS KMS.
      * Operators manage secrets, groups, and mappings from one web UI.

   .. container:: hero-visual

      .. image:: images/splash-laptop.svg
         :alt: Confidant web UI showing the current secret editor and navigation drawer
         :class: hero-shot

.. toctree::
   :hidden:

   contents
