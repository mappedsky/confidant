import React from 'react';
import { Navigate, useParams } from 'react-router-dom';
import {
  secretDetailPath,
  secretHistoryPath,
  secretVersionPath,
} from '../utils/resourceIds';
import { parseSecretRouteRemainder } from '../utils/secretRouteParams';

type RouteParams = {
  '*': string;
};

export default function SecretRouteResolver() {
  const params = useParams<RouteParams>();
  const route = parseSecretRouteRemainder(params['*']);

  if (!route.id) {
    return <Navigate to="/secrets" replace />;
  }
  if (route.isHistory) {
    return <Navigate to={secretHistoryPath(route.id)} replace />;
  }
  if (route.version !== null) {
    return <Navigate to={secretVersionPath(route.id, route.version)} replace />;
  }
  return <Navigate to={secretDetailPath(route.id)} replace />;
}
