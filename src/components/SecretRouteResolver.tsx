import React from 'react';
import { Navigate, useParams } from 'react-router-dom';
import SecretDetailPage from '../pages/SecretDetailPage';
import SecretHistoryPage from '../pages/SecretHistoryPage';
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
    return <SecretHistoryPage />;
  }
  return <SecretDetailPage />;
}
