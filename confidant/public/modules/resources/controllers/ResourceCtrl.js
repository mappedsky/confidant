(function(angular) {
    'use strict';

    angular.module('confidant.resources.controllers.ResourceCtrl', [
        'ui.router',
        'confidant.resources.services'
    ])

    .controller('resources.ResourceCtrl', [
        '$scope',
        '$stateParams',
        '$q',
        '$location',
        '$log',
        'credentials.CredentialListService',
        'services.ServiceListService',
        function ($scope, $stateParams, $q, $location, $log, CredentialListService, ServiceListService) {
            $scope.credentialList = [];
            $scope.serviceList = [];
            $scope.typeFilter = 'credentials';
            if ($stateParams.typeFilter) {
                $scope.typeFilter = $stateParams.typeFilter;
            }

            $scope.getCredentialList = CredentialListService.getCredentialList;
            $scope.$watch('getCredentialList()', function(newCredentialList, oldCredentialList) {
                if(newCredentialList !== oldCredentialList) {
                    $scope.credentialList = newCredentialList;
                }
            });
            $scope.$emit('updateCredentialList');

            $scope.getServiceList = ServiceListService.getServiceList;
            $scope.$watch('getServiceList()', function(newServiceList, oldServiceList) {
                if(newServiceList !== oldServiceList) {
                    $scope.serviceList = newServiceList;
                }
            });
            $scope.$emit('updateServiceList');

            $scope.setTypeFilter = function(type) {
                $scope.typeFilter = type;
            };

            $scope.resourceRegexFilter = function(field, regex) {
                return function(resource) {
                    var pattern = new RegExp(regex, 'ig');
                    return pattern.test(resource[field]);
                };
            };

            $scope.gotoResource = function(resource, type) {
                $location.path('/resources/' + type + '/' + resource.id);
            };

            $scope.showResource = function(resource) {
                if (resource.enabled || $scope.showDisabled) {
                    return true;
                }
                return false;
            };

        }]);

})(window.angular);
