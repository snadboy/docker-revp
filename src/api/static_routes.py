"""Static routes CRUD API endpoints for Docker Reverse Proxy."""
from typing import List, Dict, Any, Optional
import asyncio

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from ..logger import api_logger
from ..static_routes import StaticRoute


router = APIRouter(prefix="/api/static-routes", tags=["static-routes"])


class StaticRouteCreate(BaseModel):
    """Model for creating a new static route."""
    domain: str
    backend_url: str
    backend_path: str = "/"
    force_ssl: bool = True
    support_websocket: bool = False
    tls_insecure_skip_verify: bool = False
    cloudflare_tunnel: bool = False


class StaticRouteUpdate(BaseModel):
    """Model for updating an existing static route."""
    domain: str
    backend_url: str
    backend_path: str = "/"
    force_ssl: bool = True
    support_websocket: bool = False
    tls_insecure_skip_verify: bool = False
    cloudflare_tunnel: bool = False


class StaticRouteResponse(BaseModel):
    """Model for static route API responses."""
    domain: str
    backend_url: str
    backend_path: str
    force_ssl: bool
    support_websocket: bool
    tls_insecure_skip_verify: bool
    cloudflare_tunnel: bool
    # DNS validation status
    dns_resolved: Optional[bool] = None
    backend_host: Optional[str] = None
    backend_ip: Optional[str] = None
    dns_error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Model for error responses."""
    error: str
    detail: Optional[str] = None


@router.get("", response_model=List[StaticRouteResponse])
async def list_static_routes(request: Request) -> List[StaticRouteResponse]:
    """
    List all configured static routes.
    
    Returns:
        List of static route configurations
    """
    api_logger.info("API: Listing static routes")
    
    if not request.app.state.static_routes_manager:
        raise HTTPException(status_code=503, detail="Static routes manager not initialized")
    
    try:
        static_routes = request.app.state.static_routes_manager.get_routes()
        
        # Convert to response format
        routes_response = []
        for route in static_routes:
            routes_response.append(StaticRouteResponse(
                domain=route.domain,
                backend_url=route.backend_url,
                backend_path=route.backend_path,
                force_ssl=route.force_ssl,
                support_websocket=route.support_websocket,
                tls_insecure_skip_verify=route.tls_insecure_skip_verify,
                cloudflare_tunnel=route.cloudflare_tunnel,
                dns_resolved=route.dns_resolved,
                backend_host=route.backend_host,
                backend_ip=route.backend_ip,
                dns_error=route.dns_error
            ))
        
        api_logger.info(f"API: Retrieved {len(routes_response)} static routes")
        return routes_response
        
    except Exception as e:
        api_logger.error(f"API: Error listing static routes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{domain}", response_model=StaticRouteResponse)
async def get_static_route(domain: str, request: Request) -> StaticRouteResponse:
    """
    Get a specific static route by domain.
    
    Args:
        domain: Domain name of the route
        
    Returns:
        Static route configuration
    """
    api_logger.info(f"API: Getting static route for domain: {domain}")
    
    if not request.app.state.static_routes_manager:
        raise HTTPException(status_code=503, detail="Static routes manager not initialized")
    
    try:
        route = request.app.state.static_routes_manager.get_route_by_domain(domain)
        
        if not route:
            raise HTTPException(status_code=404, detail=f"Static route with domain '{domain}' not found")
        
        return StaticRouteResponse(
            domain=route.domain,
            backend_url=route.backend_url,
            backend_path=route.backend_path,
            force_ssl=route.force_ssl,
            support_websocket=route.support_websocket,
            tls_insecure_skip_verify=route.tls_insecure_skip_verify,
            cloudflare_tunnel=route.cloudflare_tunnel
        )
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"API: Error getting static route for domain {domain}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=StaticRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_static_route(route_data: StaticRouteCreate, request: Request) -> StaticRouteResponse:
    """
    Create a new static route.
    
    Args:
        route_data: Static route configuration
        
    Returns:
        Created static route configuration
    """
    api_logger.info(f"API: Creating static route for domain: {route_data.domain}")
    
    if not request.app.state.static_routes_manager:
        raise HTTPException(status_code=503, detail="Static routes manager not initialized")
    
    try:
        # Validate and create StaticRoute object
        static_route = StaticRoute(
            domain=route_data.domain,
            backend_url=route_data.backend_url,
            backend_path=route_data.backend_path,
            force_ssl=route_data.force_ssl,
            support_websocket=route_data.support_websocket,
            tls_insecure_skip_verify=route_data.tls_insecure_skip_verify,
            cloudflare_tunnel=route_data.cloudflare_tunnel
        )
        
        # Check if route already exists
        existing_route = request.app.state.static_routes_manager.get_route_by_domain(route_data.domain)
        if existing_route:
            raise HTTPException(
                status_code=409, 
                detail=f"Static route with domain '{route_data.domain}' already exists"
            )
        
        # Add the route
        success = request.app.state.static_routes_manager.add_route(static_route)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create static route")
        
        api_logger.info(f"API: Successfully created static route for domain: {route_data.domain}")
        
        return StaticRouteResponse(
            domain=static_route.domain,
            backend_url=static_route.backend_url,
            backend_path=static_route.backend_path,
            force_ssl=static_route.force_ssl,
            support_websocket=static_route.support_websocket,
            tls_insecure_skip_verify=static_route.tls_insecure_skip_verify,
            cloudflare_tunnel=static_route.cloudflare_tunnel
        )
        
    except ValidationError as e:
        api_logger.warning(f"API: Validation error creating static route: {e}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"API: Error creating static route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{domain}", response_model=StaticRouteResponse)
async def update_static_route(
    domain: str, 
    route_data: StaticRouteUpdate, 
    request: Request
) -> StaticRouteResponse:
    """
    Update an existing static route.
    
    Args:
        domain: Current domain name of the route
        route_data: Updated static route configuration
        
    Returns:
        Updated static route configuration
    """
    api_logger.info(f"API: Updating static route for domain: {domain}")
    
    if not request.app.state.static_routes_manager:
        raise HTTPException(status_code=503, detail="Static routes manager not initialized")
    
    try:
        # Check if route exists
        existing_route = request.app.state.static_routes_manager.get_route_by_domain(domain)
        if not existing_route:
            raise HTTPException(
                status_code=404, 
                detail=f"Static route with domain '{domain}' not found"
            )
        
        # Validate and create updated StaticRoute object
        updated_route = StaticRoute(
            domain=route_data.domain,
            backend_url=route_data.backend_url,
            backend_path=route_data.backend_path,
            force_ssl=route_data.force_ssl,
            support_websocket=route_data.support_websocket,
            tls_insecure_skip_verify=route_data.tls_insecure_skip_verify,
            cloudflare_tunnel=route_data.cloudflare_tunnel
        )
        
        # If domain is changing, check for conflicts
        if domain != route_data.domain:
            existing_new_domain = request.app.state.static_routes_manager.get_route_by_domain(route_data.domain)
            if existing_new_domain:
                raise HTTPException(
                    status_code=409,
                    detail=f"Static route with domain '{route_data.domain}' already exists"
                )
        
        # Update the route
        success = request.app.state.static_routes_manager.update_route(domain, updated_route)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update static route")
        
        api_logger.info(f"API: Successfully updated static route for domain: {domain}")
        
        return StaticRouteResponse(
            domain=updated_route.domain,
            backend_url=updated_route.backend_url,
            backend_path=updated_route.backend_path,
            force_ssl=updated_route.force_ssl,
            support_websocket=updated_route.support_websocket,
            tls_insecure_skip_verify=updated_route.tls_insecure_skip_verify,
            cloudflare_tunnel=updated_route.cloudflare_tunnel
        )
        
    except ValidationError as e:
        api_logger.warning(f"API: Validation error updating static route: {e}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"API: Error updating static route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{domain}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_static_route(domain: str, request: Request):
    """
    Delete a static route by domain.
    
    Args:
        domain: Domain name of the route to delete
    """
    api_logger.info(f"API: Deleting static route for domain: {domain}")
    
    if not request.app.state.static_routes_manager:
        raise HTTPException(status_code=503, detail="Static routes manager not initialized")
    
    try:
        # Check if route exists
        existing_route = request.app.state.static_routes_manager.get_route_by_domain(domain)
        if not existing_route:
            raise HTTPException(
                status_code=404, 
                detail=f"Static route with domain '{domain}' not found"
            )
        
        # Delete the route
        success = request.app.state.static_routes_manager.delete_route(domain)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete static route")
        
        api_logger.info(f"API: Successfully deleted static route for domain: {domain}")
        
        # Return 204 No Content (FastAPI handles this automatically)
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"API: Error deleting static route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/info/file", response_model=Dict[str, Any])
async def get_static_routes_file_info(request: Request) -> Dict[str, Any]:
    """
    Get information about the static routes configuration file.
    
    Returns:
        File information including path, size, modification time, etc.
    """
    api_logger.info("API: Getting static routes file info")
    
    if not request.app.state.static_routes_manager:
        raise HTTPException(status_code=503, detail="Static routes manager not initialized")
    
    try:
        file_info = request.app.state.static_routes_manager.get_file_info()
        return file_info
        
    except Exception as e:
        api_logger.error(f"API: Error getting static routes file info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/validate", response_model=Dict[str, str])
async def validate_static_route_data(route_data: StaticRouteCreate, request: Request) -> Dict[str, str]:
    """
    Validate static route data without creating the route.
    
    Args:
        route_data: Static route configuration to validate
        
    Returns:
        Validation result
    """
    api_logger.info(f"API: Validating static route data for domain: {route_data.domain}")
    
    if not request.app.state.static_routes_manager:
        raise HTTPException(status_code=503, detail="Static routes manager not initialized")
    
    try:
        # Validate using StaticRoute model
        static_route = StaticRoute(
            domain=route_data.domain,
            backend_url=route_data.backend_url,
            backend_path=route_data.backend_path,
            force_ssl=route_data.force_ssl,
            support_websocket=route_data.support_websocket,
            tls_insecure_skip_verify=route_data.tls_insecure_skip_verify,
            cloudflare_tunnel=route_data.cloudflare_tunnel
        )
        
        # Check for domain conflicts
        existing_route = request.app.state.static_routes_manager.get_route_by_domain(route_data.domain)
        if existing_route:
            return {
                "status": "warning",
                "message": f"Domain '{route_data.domain}' already exists"
            }
        
        return {
            "status": "valid",
            "message": "Route configuration is valid"
        }
        
    except ValidationError as e:
        return {
            "status": "invalid",
            "message": f"Validation error: {str(e)}"
        }
    except Exception as e:
        api_logger.error(f"API: Error validating static route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/recheck-dns", response_model=Dict[str, Any])
async def recheck_static_routes_dns(request: Request) -> Dict[str, Any]:
    """
    Recheck DNS resolution for all static routes.
    
    Returns:
        Summary of DNS recheck results
    """
    api_logger.info("API: Rechecking DNS for all static routes")
    
    if not request.app.state.static_routes_manager:
        raise HTTPException(status_code=503, detail="Static routes manager not initialized")
    
    try:
        # Get all routes and perform DNS validation
        routes = request.app.state.static_routes_manager.get_routes()
        
        # Revalidate DNS for each route
        for route in routes:
            route.validate_dns()
        
        # Save updated routes
        request.app.state.static_routes_manager.save_routes(routes)
        
        # Update Caddy configuration if manager is available
        if request.app.state.caddy_manager:
            await request.app.state.caddy_manager.update_static_routes(routes)
        
        # Calculate results
        total_routes = len(routes)
        working_routes = sum(1 for route in routes if route.dns_resolved is True)
        dns_issues = sum(1 for route in routes if route.dns_resolved is False)
        unknown_status = total_routes - working_routes - dns_issues
        
        api_logger.info(f"DNS recheck completed: {working_routes} working, {dns_issues} issues, {unknown_status} unknown")
        
        return {
            "status": "completed",
            "total_routes": total_routes,
            "working_routes": working_routes,
            "dns_issues": dns_issues,
            "unknown_status": unknown_status,
            "message": f"DNS recheck completed for {total_routes} routes"
        }
        
    except Exception as e:
        api_logger.error(f"API: Error rechecking static routes DNS: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")