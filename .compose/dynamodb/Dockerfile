# Pinned to 2.x because 3.x has had regressions in write paths for some setups.
FROM amazon/dynamodb-local:2.5.4

USER root
RUN yum install -y util-linux && \
    yum clean all && \
    rm -rf /var/cache/yum && \
    mkdir -p /home/dynamodblocal/data && \
    chown -R dynamodblocal:dynamodblocal /home/dynamodblocal/data
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
