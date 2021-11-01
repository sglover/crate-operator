import logging

import kopf
from kopf import DiffItem, DiffOperation

from crate.operator.config import config
from crate.operator.constants import LABEL_NAME
from crate.operator.edge import notify_service_ip


async def external_ip_changed(
    name: str,
    namespace: str,
    diff: kopf.Diff,
    meta: dict,
    logger: logging.Logger,
):
    # Ignore the testing service
    if config.TESTING and name.startswith("crate-testing"):
        return

    if len(diff) == 0:
        return

    op: DiffItem = diff[0]

    # Don't care about IPs being removed (also does not happen)
    if op.operation == DiffOperation.REMOVE:
        return

    # Sometimes when a service is just created, we get an _empty_ IP added,
    # also ignore these.
    if not op.new:
        return

    cluster_id = meta["labels"][LABEL_NAME]

    if len(op.new) == 0:
        logger.warning(f"No IP received for LoadBalancer {diff}")
        return

    # Most k8s clusters give out IP addresses to LoadBalancer services, however some
    # (i.e. EKS) give hostnames instead. As far as Crate is concerned, these are
    # treated the same.
    # TODO: Multiple IPs?
    ip = op.new[0].get("ip") or op.new[0].get("hostname")
    if not ip:
        logger.warning(f"Load balancer got neither IP nor hostname {op}")
        return
    await notify_service_ip(namespace, cluster_id, ip, logger)