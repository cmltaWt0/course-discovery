import logging

from django.contrib.auth.models import Group
from course_discovery.apps.publisher.assign_permissions import assign_permissions

from course_discovery.apps.publisher.choices import CourseRunStateChoices, CourseStateChoices, PublisherUserRole
from course_discovery.apps.publisher.models import (Course, CourseRun, CourseRunState, CourseState, CourseUserRole,
                                                    OrganizationExtension, Seat)

logger = logging.getLogger(__name__)


def process_course(meta_data_course):
    """ Create or update the course."""

    # if course has more than 1 organization don't import that course. Just log the entry.
    # that course will import manually.
    organizations = meta_data_course.authoring_organizations.all()

    try:
        available_organization = organizations_requirements(organizations, meta_data_course)

        if not available_organization:
            return

        create_or_update_course(meta_data_course, available_organization)

    except:  # pylint: disable=bare-except
        logger.error('Exception appear for course-id [%s].', meta_data_course.uuid)


def create_or_update_course(meta_data_course, available_organization):

    defaults = {
        'title': meta_data_course.title, 'number': meta_data_course.number,
        'short_description': meta_data_course.short_description,
        'full_description': meta_data_course.full_description,
        'level_type': meta_data_course.level_type
    }

    publisher_course, created = Course.objects.update_or_create(
        course_metadata_pk=meta_data_course.id,
        defaults=defaults
    )

    for i, subject in enumerate(meta_data_course.subjects.all()):
        if i == 0:
            publisher_course.primary_subject = subject
        elif i == 1:
            publisher_course.secondary_subject = subject
        elif i == 2:
            publisher_course.tertiary_subject = subject

    publisher_course.save()

    if created:
        if available_organization:
            publisher_course.organizations.add(available_organization)

            # assign course-user-roles
            assign_course_user_roles(publisher_course, available_organization)

        # marked course as approved with related fields.
        state, created = CourseState.objects.get_or_create(course=publisher_course)
        if created:
            state.approved_by_role = PublisherUserRole.MarketingReviewer
            state.owner_role = PublisherUserRole.MarketingReviewer
            state.marketing_reviewed = True
            state.name = CourseStateChoices.Approved
            state.save()

        logger.info('Import course with id [%s], number [%s].', publisher_course.id, publisher_course.number)

    # create canonical course-run against the course.
    create_course_runs(meta_data_course, publisher_course)


def create_course_runs(meta_data_course, publisher_course):
        # create or update canonical course-run for the course.
        canonical_course_run = meta_data_course.canonical_course_run

        if canonical_course_run and canonical_course_run.key:
            defaults = {
                'course': publisher_course,
                'start': canonical_course_run.start, 'end': canonical_course_run.end,
                'enrollment_start': canonical_course_run.enrollment_start,
                'enrollment_end': canonical_course_run.enrollment_end,
                'min_effort': canonical_course_run.min_effort, 'max_effort': canonical_course_run.max_effort,
                'language': canonical_course_run.language, 'pacing_type': canonical_course_run.pacing_type,
                'length': canonical_course_run.weeks_to_complete,
                'card_image_url': canonical_course_run.card_image_url,
                'lms_course_id': canonical_course_run.key
            }

            publisher_course_run, created = CourseRun.objects.update_or_create(
                lms_course_id=canonical_course_run.key, defaults=defaults
            )

            # add many to many fields.
            publisher_course_run.transcript_languages.add(*canonical_course_run.transcript_languages.all())
            publisher_course_run.staff.add(*canonical_course_run.staff.all())
            publisher_course_run.language = canonical_course_run.language

            # Initialize workflow for Course-run.
            if created:
                state, created = CourseRunState.objects.get_or_create(course_run=publisher_course_run)
                if created:
                    state.approved_by_role = PublisherUserRole.ProjectCoordinator
                    state.owner_role = PublisherUserRole.Publisher
                    state.preview_accepted = True
                    state.name = CourseRunStateChoices.Published
                    state.save()

                logger.info(
                    'Import course-run with id [%s], lms_course_id [%s].',
                    publisher_course_run.id, publisher_course_run.lms_course_id
                )

            # create seat against the course-run.
            create_seats(canonical_course_run, publisher_course_run)

        else:
            logger.warning(
                'Canonical course-run not found for metadata course [%s].', meta_data_course.uuid
            )


def create_seats(metadata_course_run, publisher_course_run):
    # create or update canonical course-run related seats..
    seats = metadata_course_run.seats.all()
    if seats:
        for metadata_seat in seats:
            defaults = {
                'price': metadata_seat.price, 'currency': metadata_seat.currency,
                'credit_provider': metadata_seat.credit_provider, 'credit_hours': metadata_seat.credit_hours,
                'upgrade_deadline': metadata_seat.upgrade_deadline
            }

            seat, created = Seat.objects.update_or_create(
                course_run=publisher_course_run,
                type=metadata_seat.type,
                defaults=defaults
            )

            if created:
                logger.info(
                    'Import seat with id [%s], type [%s].',
                    seat.id, metadata_course_run.type
                )

    else:
        logger.warning(
            'No seats found for course-run [%s].', metadata_course_run.uuid
        )


def assign_course_user_roles(course, organization):
    # Assign the course user roles against each organization users.

    for user_role in organization.organization_user_roles.all():
        CourseUserRole.add_course_roles(course, user_role.role, user_role.user)


def organizations_requirements(organizations, meta_data_course):
    """ Before adding course make sure organization exists and has OrganizationExtension
    object also.
    """
    if organizations.count() > 1:
        logger.warning(
            'Course has more than 1 organization. Course uuid is [%s].', meta_data_course.uuid
        )
        return None

    available_organization = organizations.first()

    if not available_organization:
        logger.warning(
            'Course has no organization. Course uuid is [%s].', meta_data_course.uuid
        )
        return None

    if available_organization.key.strip() == "":
        logger.warning(
            'Organization key has empty value [%s].', available_organization.uuid
        )
        return None

    group, __ = Group.objects.get_or_create(
        name__iexact=available_organization.key, defaults={'name': available_organization.key}
    )

    organization_extension = OrganizationExtension.objects.filter(organization=available_organization)

    if not organization_extension.exists():
        organization_extension, __ = OrganizationExtension.objects.get_or_create(
            organization=available_organization,
            group=group
        )
    else:
        organization_extension = organization_extension.first()

    assign_permissions(organization_extension)
    return organization_extension.organization
